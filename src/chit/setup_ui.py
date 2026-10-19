"""First-run window: download the models, then find the fastest chip for each."""

import os
import queue
import shutil
import threading
import tkinter as tk
from tkinter import ttk

from PIL import ImageTk

from . import bench, models, paths
from .icon import app_icon
from .log import log

BG = "#16161a"
FG = "#ececf0"
DIM = "#9a9aa6"
ACCENT = "#7c5cff"

REQUIRED_DISK_SPACE = 3 * 1024 * 1024 * 1024  # ~3 GB

MODEL_SIZES = {
    models.ASR_REPO: 240 * 1024 * 1024,
    models.LLM_REPO: 1200 * 1024 * 1024,
}
DEFAULT_MODEL_SIZE = 700 * 1024 * 1024


def format_size(size_bytes):
    """Format bytes into a human-readable string (e.g. '1.4 GB', '250 MB')."""
    if size_bytes >= 1024**3:
        val = size_bytes / (1024**3)
        return f"{val:.1f} GB"
    if size_bytes >= 1024**2:
        val = size_bytes / (1024**2)
        return f"{val:.0f} MB"
    if size_bytes >= 1024:
        val = size_bytes / 1024
        return f"{val:.0f} KB"
    return f"{size_bytes} B"


def get_free_disk_space(target_path=None):
    """Returns free disk space in bytes for the drive containing target_path (defaults to %LOCALAPPDATA%)."""
    p = str(target_path or os.environ.get("LOCALAPPDATA") or paths.DATA_DIR)
    p = os.path.abspath(p)
    while not os.path.exists(p) and os.path.dirname(p) != p:
        p = os.path.dirname(p)
    try:
        return shutil.disk_usage(p).free
    except OSError:
        return 0


def check_disk_space(target_path=None, required_bytes=REQUIRED_DISK_SPACE):
    """Check if free disk space on the target path's drive meets the requirement.

    Returns (has_space: bool, free_bytes: int, required_bytes: int).
    """
    free_bytes = get_free_disk_space(target_path)
    return free_bytes >= required_bytes, free_bytes, required_bytes


def get_drive_name(target_path=None):
    """Returns the drive or mount point name for target_path."""
    p = os.path.abspath(str(target_path or os.environ.get("LOCALAPPDATA") or paths.DATA_DIR))
    drive, _ = os.path.splitdrive(p)
    return drive if drive else p


def calculate_download_size(repos=None, use_remote=True):
    """Calculate the total download size for the given model repos.

    Skips any repos that have already been downloaded.
    If use_remote is True, tries querying models.remote_size(repo),
    falling back to known MODEL_SIZES on failure.
    """
    if repos is None:
        repos = [models.ASR_REPO, models.LLM_REPO]

    total = 0
    for repo in repos:
        if models.is_downloaded(repo):
            continue
        if use_remote:
            try:
                size, _ = models.remote_size(repo)
                total += size
                continue
            except Exception:
                pass
        total += MODEL_SIZES.get(repo, DEFAULT_MODEL_SIZE)
    return total


def run_setup(settings):
    """Returns True when Chit is ready to use, False if the user closed the window."""
    root = tk.Tk()
    root.title("Chit setup")
    root.configure(bg=BG)
    root.resizable(False, False)
    s = root.winfo_fpixels("1i") / 96.0
    w, h = int(480 * s), int(260 * s)
    root.geometry(f"{w}x{h}+{(root.winfo_screenwidth() - w) // 2}+{(root.winfo_screenheight() - h) // 3}")
    icon = ImageTk.PhotoImage(app_icon(64))
    root.iconphoto(True, icon)

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        "Chit.Horizontal.TProgressbar",
        troughcolor="#2a2a31",
        background=ACCENT,
        bordercolor="#2a2a31",
        lightcolor=ACCENT,
        darkcolor=ACCENT,
        thickness=int(8 * s),
    )

    pad = int(24 * s)
    top = tk.Frame(root, bg=BG)
    top.pack(fill="x", padx=pad, pady=(pad, 0))
    tk.Label(top, image=icon, bg=BG).pack(side="left")
    title = tk.Label(top, text="Setting up Chit", bg=BG, fg=FG, font=("Segoe UI Semibold", 15))
    title.pack(side="left", padx=int(12 * s))

    def make_body_text(dl_bytes, free_b, req_b):
        dl_str = format_size(dl_bytes)
        free_str = format_size(free_b)
        req_str = format_size(req_b)
        if dl_bytes > 0:
            return (
                f"Downloading the speech and writing models (about {dl_str}, one time only). "
                f"Free disk space: {free_str} available ({req_str} required). "
                "After this, Chit works fully offline."
            )
        return (
            f"Speech and writing models are already downloaded. "
            f"Free disk space: {free_str} available ({req_str} required). "
            "After this, Chit works fully offline."
        )

    download_size = calculate_download_size()
    _, free_bytes, req_bytes = check_disk_space()

    body = tk.Label(
        root,
        text=make_body_text(download_size, free_bytes, req_bytes),
        bg=BG,
        fg=DIM,
        font=("Segoe UI", 10),
        wraplength=w - 2 * pad,
        justify="left",
    )
    body.pack(fill="x", padx=pad, pady=(int(14 * s), int(10 * s)))
    bar = ttk.Progressbar(root, style="Chit.Horizontal.TProgressbar", maximum=1000)
    bar.pack(fill="x", padx=pad)
    status_init = (
        f"Total download: {format_size(download_size)} • Free space: {format_size(free_bytes)}"
        if download_size > 0
        else f"Models downloaded • Free space: {format_size(free_bytes)}"
    )
    status = tk.Label(root, text=status_init, bg=BG, fg=DIM, font=("Segoe UI", 9), anchor="w")
    status.pack(fill="x", padx=pad, pady=(int(6 * s), 0))
    buttons = tk.Frame(root, bg=BG)
    buttons.pack(fill="x", padx=pad, pady=int(12 * s), side="bottom")

    events = queue.Queue()
    result = {"ok": False}

    def work():
        try:
            # Check free disk space before downloading
            has_space, free_b, req_b = check_disk_space()
            if not has_space:
                events.put(("disk_error", free_b, req_b))
                return

            # Download weights: 20% speech model, 60% writing model, 20% optimizing.
            plan = [(models.ASR_REPO, 0.0, 0.2, "speech model"), (models.LLM_REPO, 0.2, 0.8, "writing model")]
            for repo, lo, hi, label in plan:

                def progress(done, total, lo=lo, hi=hi, label=label):
                    frac = done / total if total else 0
                    events.put(
                        (
                            "progress",
                            lo + (hi - lo) * frac,
                            f"Downloading {label}: {done / 1e6:.0f} of {total / 1e6:.0f} MB",
                        )
                    )

                models.download(repo, progress)
            events.put(
                (
                    "phase",
                    "Optimizing for your PC",
                    "Finding the fastest chip on this PC for speech and for writing. "
                    "This one-time step can take a few minutes.",
                )
            )
            steps = iter([0.84, 0.88, 0.92, 0.95, 0.97, 0.99])
            asr, llm, asr_t, llm_t = bench.pick_devices(lambda msg: events.put(("progress", next(steps, 0.99), msg)))
            settings.set("asr_device", asr)
            settings.set("llm_device", llm)
            settings.set("setup_version", models.SETUP_VERSION)
            log(f"Setup complete: speech on {asr} {asr_t}, writing on {llm} {llm_t}")
            events.put(("done", asr, llm))
        except Exception as e:
            log(f"Setup failed: {e!r}")
            events.put(("error", str(e)))

    def start():
        dl = calculate_download_size()
        _, free_b, req_b = check_disk_space()
        title["text"] = "Setting up Chit"
        body["text"] = make_body_text(dl, free_b, req_b)
        status["text"] = (
            f"Total download: {format_size(dl)} • Free space: {format_size(free_b)}"
            if dl > 0
            else f"Models downloaded • Free space: {format_size(free_b)}"
        )
        bar["value"] = 0
        for child in buttons.winfo_children():
            child.destroy()
        tk.Button(
            buttons,
            text="Cancel",
            command=root.destroy,
            bg="#2a2a31",
            fg=FG,
            relief="flat",
            activebackground="#3a3a44",
            activeforeground=FG,
            padx=int(14 * s),
        ).pack(side="right")
        threading.Thread(target=work, daemon=True).start()

    def poll():
        try:
            while True:
                ev = events.get_nowait()
                if ev[0] == "progress":
                    bar["value"] = int(ev[1] * 1000)
                    status["text"] = ev[2]
                elif ev[0] == "phase":
                    title["text"], body["text"] = ev[1], ev[2]
                elif ev[0] == "disk_error":
                    free_b, req_b = ev[1], ev[2]
                    drive = get_drive_name()
                    drive_text = f"drive {drive}" if drive.endswith(":") else drive
                    title["text"] = "Not enough disk space"
                    body["text"] = (
                        f"Chit requires at least {format_size(req_b)} of free disk space on {drive_text} "
                        f"to download and set up models, but only {format_size(free_b)} is available.\n\n"
                        f"Please free up some disk space and try again."
                    )
                    status["text"] = f"Required: {format_size(req_b)} • Available: {format_size(free_b)}"
                    bar["value"] = 0
                    for child in buttons.winfo_children():
                        child.destroy()
                    tk.Button(
                        buttons,
                        text="Try again",
                        command=start,
                        bg=ACCENT,
                        fg="white",
                        relief="flat",
                        padx=int(14 * s),
                    ).pack(side="right")
                    tk.Button(
                        buttons,
                        text="Quit",
                        command=root.destroy,
                        bg="#2a2a31",
                        fg=FG,
                        relief="flat",
                        padx=int(14 * s),
                    ).pack(side="right", padx=int(8 * s))
                elif ev[0] == "done":
                    bar["value"] = 1000
                    names = {"CPU": "processor", "GPU": "graphics chip", "NPU": "AI chip (NPU)"}
                    title["text"] = "Chit is ready"
                    body["text"] = (
                        "Click into any text box and hold Caps Lock. When you hear the chime, talk, "
                        "then release. Tapping Caps Lock still works as usual. Double-tap it for "
                        "hands-free, and double-tap again to finish."
                    )
                    status["text"] = (
                        f"Speech runs on your {names.get(ev[1], ev[1])}, "
                        f"writing cleanup on your {names.get(ev[2], ev[2])}."
                    )
                    result["ok"] = True
                    for child in buttons.winfo_children():
                        child.destroy()
                    tk.Button(
                        buttons,
                        text="Start using Chit",
                        command=root.destroy,
                        bg=ACCENT,
                        fg="white",
                        relief="flat",
                        activebackground="#6a4af0",
                        activeforeground="white",
                        padx=int(14 * s),
                    ).pack(side="right")
                    root.after(8000, root.destroy)
                elif ev[0] == "error":
                    title["text"] = "Setup couldn't finish"
                    body["text"] = (
                        "Check your internet connection and try again. Anything already "
                        "downloaded is kept.\n\n" + ev[1][:180]
                    )
                    for child in buttons.winfo_children():
                        child.destroy()
                    tk.Button(
                        buttons, text="Try again", command=start, bg=ACCENT, fg="white", relief="flat", padx=int(14 * s)
                    ).pack(side="right")
                    tk.Button(
                        buttons, text="Quit", command=root.destroy, bg="#2a2a31", fg=FG, relief="flat", padx=int(14 * s)
                    ).pack(side="right", padx=int(8 * s))
        except queue.Empty:
            pass
        if root.winfo_exists():
            root.after(150, poll)

    start()
    root.after(150, poll)
    root.mainloop()
    return result["ok"]
