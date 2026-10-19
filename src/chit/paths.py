"""Where Chit keeps its files."""

import os
import sys

APP_NAME = "Chit"
DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), APP_NAME)
MODELS_DIR = os.path.join(DATA_DIR, "models")
OV_CACHE_DIR = os.path.join(DATA_DIR, "ov-cache")
LOG_PATH = os.path.join(DATA_DIR, "chit.log")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")

FROZEN = getattr(sys, "frozen", False)


def asset(name):
    """Path to a file shipped in chit/assets, both from source and in the built app."""
    if FROZEN:
        return os.path.join(sys._MEIPASS, "chit", "assets", name)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", name)
