"""PyInstaller entry script for Chit.exe."""

import multiprocessing
import sys

if __name__ == "__main__":
    multiprocessing.freeze_support()  # the keyboard-hook helper is a spawned process
    from chit.app import main

    sys.exit(main())
