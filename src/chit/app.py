"""Chit's main app: hotkey gestures -> mic -> phrase-by-phrase Whisper -> cleanup -> paste.

Threads:
  control  owns the gesture state machine, the mic stream and the segmenter; everything
           that changes recording state happens here, in order (key events, clicks, Esc,
           audio blocks, timers)
  worker   voice check + Whisper for each phrase as it arrives, then cleanup + paste
           when a dictation finishes (so "release -> text" only waits for the last phrase)
  loader   loads the models at startup without blocking the UI
  Tk main  the bottom bar; pystray runs the tray icon on its own thread
"""

import argparse
import ctypes
import queue
import sys
import threading
import time
from collections import deque

import numpy as np

from . import log as logmod
from . import sounds
from .audio import FileStream, MicStream, Segmenter
from .config import Settings
from .gesture import Gestures
from .log import log, log_text

VK_CAPITAL = 0x14
HANDS_FREE_IDLE_S = 60  # hands-free stops itself after this long without a voice
MAX_DICTATION_S = 600  # hard cap per dictation
MIC_STALL_S = 5  # no audio from the mic for this long = it died
MIN_VOICE_S = 0.3  # phrases with less actual voice than this are noise


class Session:
    def __init__(self, sid):
        now = time.monotonic()
        self.id = sid
        self.texts = []
        self.language = None
        self.cancelled = False
        self.confirmed = True  # dictation only starts on a real hold / double-tap / click
        self.started = now
        self.last_voice = now
        self.last_audio = now


class App:
    def __init__(self, args, settings):
        self.args = args
        self.settings = settings
        self.ready = False
        self.whisper = self.cleaner = self.vad = self.inserter = None
        self.asr_device = self.llm_device = None
        self.recording = False
        self.hands_free = False
        self.session = None
        self.sid = 0
        self.pending = 0
        self.levels = deque(maxlen=32)
        self.events = queue.Queue()
        self.jobs = queue.Queue()
        self.stream = None
        self.segmenter = Segmenter(self._on_phrase)
        self.gestures = Gestures(
            start=self._start, finish=self._finish, cancel=self._cancel, hands_free=self._set_hands_free
        )
        self.overlay = self.tray = self.hook = None

    # ------------------------------------------------------------------ #
    # Thread-safe entry points (hook helper, bar, tray)
    # ------------------------------------------------------------------ #
    def on_hook(self, msg):
        """Messages from the keyboard helper: hold / tap / key / esc (see hotkey.py)."""
        self.events.put(msg)

    def on_click(self):
        self.events.put(("click",))

    def ui_state(self):
        s = self.session
        if self.recording and s and s.confirmed:
            return "listening", self.hands_free
        if self.pending:
            return "thinking", False
        return "idle", False

    def set_setting(self, key, value):
        self.settings.set(key, value)
        if key == "debug_log":
            logmod.debug_text = value
        log(f"Setting {key} = {value}")

    def device_summary(self):
        if not self.ready:
            return "Loading models..."
        llm = self.llm_device or "not loaded"
        return f"Speech on {self.asr_device} · Cleanup on {llm}"

    def quit(self):
        self.events.put(("quit",))

    # ------------------------------------------------------------------ #
    # Startup
    # ------------------------------------------------------------------ #
    def _load(self):
        from . import models
        from .asr import Whisper
        from .cleanup import Cleaner, SmartCleaner
        from .insert import Inserter
        from .vad import VoiceDetector

        t = time.perf_counter()
        try:
            # Before anything is loaded (nothing holds the files open yet): drop compiled
            # caches that the chosen devices don't use.
            from .bench import cache_dir, prune_caches

            prune_caches({cache_dir("asr", self.settings["asr_device"]), cache_dir("llm", self.settings["llm_device"])})
            self.vad = VoiceDetector()
            self.inserter = Inserter()
            self.whisper, self.asr_device = _load_on(
                Whisper, "asr", models.local_path(models.ASR_REPO), self.settings["asr_device"]
            )
            self.cleaner = Cleaner(None)
            self.ready = True
            log(f"Speech model ready on {self.asr_device} in {time.perf_counter() - t:.1f}s")
        except Exception as e:
            log(f"Could not load the speech model: {e}")
            self.overlay and self.overlay.show_message("Chit couldn't start - see log", error=True, seconds=8)
            return
        # The cleanup model loads second; until then cleanup falls back to the rules.
        try:
            smart, self.llm_device = _load_on(
                SmartCleaner, "llm", models.local_path(models.LLM_REPO), self.settings["llm_device"]
            )
            self.cleaner.smart = smart
            log(f"Cleanup model ready on {self.llm_device} ({time.perf_counter() - t:.1f}s total)")
        except Exception as e:
            log(f"Cleanup model unavailable, using light cleanup: {e}")

    def run(self):
        from .hotkey import KeyHook
        from .overlay import Overlay
        from .tray import Tray

        threading.Thread(target=self._load, daemon=True, name="loader").start()
        threading.Thread(target=self._control, daemon=True, name="control").start()
        threading.Thread(target=self._worker, daemon=True, name="worker").start()
        self.hook = KeyHook(VK_CAPITAL, self.on_hook, accept_injected=self.args.test_injected_keys)
        self.overlay = Overlay(self)
        self.tray = Tray(self)
        self.tray.start(
            notify=None
            if self.args.background
            else "Chit is running. Hold Caps Lock to talk, or double-tap it for hands-free."
        )
        threading.Thread(target=self._wait_for_show_requests, daemon=True).start()
        log("Chit is running")
        self.overlay.run()  # Tk owns the main thread until Quit
        self.hook.stop()
        self.tray.stop()
        log("Bye")

    def _wait_for_show_requests(self):
        """A second launch of Chit signals this event instead of starting another copy."""
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateEventW(None, False, False, SHOW_EVENT)
        while True:
            if kernel32.WaitForSingleObject(handle, 0xFFFFFFFF) == 0 and self.overlay:
                self.overlay.show_message("Chit is running · hold Caps Lock to talk", seconds=3)

    # ------------------------------------------------------------------ #
    # Control thread
    # ------------------------------------------------------------------ #
    def _control(self):
        while True:
            try:
                ev = self.events.get(timeout=0.05)
            except queue.Empty:
                ev = None
            try:
                if ev:
                    self._handle(ev)
                self._timers()
            except Exception as e:
                log(f"Control error: {e!r}")
                self._abort("Something went wrong")

    def _handle(self, ev):
        kind = ev[0]
        if kind == "audio":
            s = self.session
            if self.recording and s:
                s.last_audio = time.monotonic()
                block = ev[1]
                self.segmenter.feed(block)
                # 25 ms levels give the on-screen graph a lively, speech-like motion.
                self.levels.extend(float(np.sqrt(np.mean(q * q))) for q in np.array_split(block, 4))
            return
        if kind == "quit":
            if self.recording:
                self._close_stream()
            self.overlay and self.overlay.quit()
            return
        if not self.ready and kind in ("hold", "tap", "key", "click"):
            if kind in ("hold", "click"):
                self.overlay and self.overlay.show_message("Chit is starting up...", seconds=2)
            return
        if kind == "hold":
            self.gestures.hold(ev[1])
        elif kind == "tap":
            self.gestures.tap(ev[1], ev[2])
        elif kind == "key":
            (self.gestures.key_down if ev[1] else self.gestures.key_up)(ev[2])
        elif kind == "esc":
            self.gestures.esc()
        elif kind == "click":
            self.gestures.click()

    def _timers(self):
        now = time.monotonic()
        self.gestures.tick(now)
        s = self.session
        if not (self.recording and s):
            return
        if now - s.last_audio > MIC_STALL_S:
            log("Microphone stopped sending audio")
            self._abort("Microphone stopped")
        elif self.hands_free and now - s.last_voice > HANDS_FREE_IDLE_S:
            log(f"No voice for {HANDS_FREE_IDLE_S}s: finishing hands-free dictation")
            self.gestures.reset()
            self._finish()
        elif now - s.started > MAX_DICTATION_S:
            log("Dictation reached the 10 minute limit")
            self.gestures.reset()
            self._finish()

    # Gesture callbacks (control thread) -------------------------------- #
    def _start(self):
        self.sid += 1
        self.session = Session(self.sid)
        self.segmenter.reset()
        self.levels.clear()
        self.hands_free = False
        try:
            put = lambda block: self.events.put(("audio", block))  # noqa: E731
            if self.args.test_audio:
                self.stream = FileStream(self.args.test_audio, put)
            else:
                self.stream = MicStream(self.settings["mic"], put)
            self.stream.start()
        except Exception as e:
            log(f"Microphone error: {e}")
            self.stream = None
            self.session = None
            self.gestures.reset()
            self._sound("error")
            self.overlay and self.overlay.show_message("No microphone found", error=True)
            return
        self.recording = True
        self.hook.set_recording(True)
        self._sound("start")  # the cue to start talking, in step with the listening pill
        self.tray and self.tray.set_listening(True)

    def _set_hands_free(self):
        self.hands_free = True

    def _finish(self):
        s = self.session
        if not (self.recording and s):
            return
        self._close_stream()
        self.segmenter.flush()  # the last phrase goes to the worker before "finalize"
        if s.confirmed:
            self._sound("stop")
        self.pending += 1
        self.jobs.put(("finalize", s))
        self._end()

    def _cancel(self):
        s = self.session
        if not (self.recording and s):
            return
        s.cancelled = True
        self._close_stream()
        self.segmenter.reset()
        if s.confirmed:
            self._sound("stop")
            log("Dictation cancelled")
        self._end()

    def _abort(self, message):
        if self.recording and self.session:
            self.session.cancelled = True
            self._close_stream()
            self.segmenter.reset()
            self._end()
        self.gestures.reset()
        self._sound("error")
        self.overlay and self.overlay.show_message(message, error=True)

    def _close_stream(self):
        if self.stream:
            try:
                self.stream.close()
            except Exception as e:
                log(f"Mic close failed: {e}")
            self.stream = None
        # Feed whatever audio already arrived for this dictation.
        pending = []
        while True:
            try:
                ev = self.events.get_nowait()
            except queue.Empty:
                break
            (self.segmenter.feed(ev[1]) if ev[0] == "audio" else pending.append(ev))
        for ev in pending:
            self.events.put(ev)

    def _end(self):
        self.recording = False
        self.hands_free = False
        self.session = None
        self.hook.set_recording(False)
        self.tray and self.tray.set_listening(False)

    def _on_phrase(self, audio):
        if self.session:
            self.jobs.put(("phrase", self.session, audio))

    def _sound(self, name):
        if self.settings["sounds"]:
            sounds.play(name)

    # ------------------------------------------------------------------ #
    # Worker thread
    # ------------------------------------------------------------------ #
    def _worker(self):
        while True:
            kind, s, *rest = self.jobs.get()
            try:
                if kind == "phrase":
                    self._transcribe(s, rest[0])
                else:
                    self._deliver(s)
            except Exception as e:
                log(f"Worker error: {e!r}")
            finally:
                if kind == "finalize":
                    self.pending -= 1

    def _transcribe(self, s, audio):
        if s.cancelled:
            return
        voiced = self.vad.voiced_seconds(audio)
        if voiced < MIN_VOICE_S:
            log(f"Ignored {len(audio) / 16000:.1f}s of noise")
            return
        s.last_voice = time.monotonic()
        lang = self.settings["language"]
        lang = None if lang == "auto" else lang
        t = time.perf_counter()
        text = self.whisper.transcribe(audio, lang or s.language)
        if not text or s.cancelled:
            return
        if s.language is None and lang is None:
            from .asr import detect_language

            s.language = detect_language(text)
        s.texts.append(text)
        log_text(f"Phrase {len(audio) / 16000:.1f}s -> {time.perf_counter() - t:.2f}s", text)

    def _deliver(self, s):
        if s.cancelled:
            return
        raw = " ".join(s.texts).strip()
        if not raw:
            if s.confirmed:
                log("Nothing was heard")
                self.overlay and self.overlay.show_message("Didn't catch that", seconds=1.6)
            return
        t = time.perf_counter()
        text = self.cleaner.clean(raw, self.settings["cleanup"])
        if text and text[-1] in ".!?।…":
            text += " "  # so the next dictation continues naturally
        self.inserter.insert(text)
        log_text(f"Inserted ({self.settings['cleanup']} cleanup {time.perf_counter() - t:.2f}s)", text)


def _load_on(cls, kind, model_dir, device):
    """Load on the benchmarked device; if that fails, fall back to the CPU."""
    from .bench import cache_dir

    device = device or "CPU"
    try:
        return cls(model_dir, device, cache_dir(kind, device)), device
    except Exception as e:
        if device == "CPU":
            raise
        log(f"{cls.__name__} failed on {device} ({e}); using CPU")
        return cls(model_dir, "CPU", cache_dir(kind, "CPU")), "CPU"


# ---------------------------------------------------------------------- #
# Entry point
# ---------------------------------------------------------------------- #
MUTEX = "Local\\ChitDictationApp"
SHOW_EVENT = "Local\\ChitShowBar"


def _claim_single_instance():
    kernel32 = ctypes.windll.kernel32
    _claim_single_instance.handle = kernel32.CreateMutexW(None, False, MUTEX)
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS: poke the running copy
        handle = kernel32.CreateEventW(None, False, False, SHOW_EVENT)
        kernel32.SetEvent(handle)
        return False
    return True


def main(argv=None):
    p = argparse.ArgumentParser(prog="Chit")
    p.add_argument("--background", action="store_true", help="started at login: no welcome notification")
    p.add_argument("--setup", action="store_true", help="re-run the first-run setup (download + benchmark)")
    # Test hooks: accept simulated key presses and use a WAV file instead of the mic.
    p.add_argument("--test-injected-keys", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--test-audio", help=argparse.SUPPRESS)
    args = p.parse_args(argv)

    logmod.setup()
    if not _claim_single_instance():
        log("Chit is already running")
        return 0
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # crisp bar on scaled displays
    except Exception:
        pass
    settings = Settings()
    logmod.debug_text = settings["debug_log"]
    log(f"Starting Chit {_version()} (python {sys.version.split()[0]})")

    from . import models

    if (
        args.setup
        or settings["setup_version"] < models.SETUP_VERSION
        or not (models.is_downloaded(models.ASR_REPO) and models.is_downloaded(models.LLM_REPO))
    ):
        from .setup_ui import run_setup

        if not run_setup(settings):
            log("Setup was not completed")
            return 1
    try:
        App(args, settings).run()
    except Exception:
        import traceback

        log("Fatal error:\n" + traceback.format_exc())
        raise
    return 0


def _version():
    from . import __version__

    return __version__
