"""First-run window: download the models, then find the fastest chip for each."""

import queue
import threading
import tkinter as tk
from tkinter import ttk

from PIL import ImageTk

from .icon import app_icon
from .log import log

BG = "#16161a"
FG = "#ececf0"
DIM = "#9a9aa6"
ACCENT = "#7c5cff"


def run_setup(settings):
    """Returns True when Chit is ready to use, False if the user closed the window."""
    from . import bench, models

    root = tk.Tk()
    root.title("Chit setup")
    root.configure(bg=BG)
    root.resizable(False, False)
    s = root.winfo_fpixels("1i") / 96.0
    w, h = int(480 * s), int(250 * s)
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
    body = tk.Label(
        root,
        text="Downloading the speech and writing models (about 1.4 GB, one time only). "
        "After this, Chit works fully offline.",
        bg=BG,
        fg=DIM,
        font=("Segoe UI", 10),
        wraplength=w - 2 * pad,
        justify="left",
    )
    body.pack(fill="x", padx=pad, pady=(int(14 * s), int(10 * s)))
    bar = ttk.Progressbar(root, style="Chit.Horizontal.TProgressbar", maximum=1000)
    bar.pack(fill="x", padx=pad)
    status = tk.Label(root, text="Starting...", bg=BG, fg=DIM, font=("Segoe UI", 9), anchor="w")
    status.pack(fill="x", padx=pad, pady=(int(6 * s), 0))
    buttons = tk.Frame(root, bg=BG)
    buttons.pack(fill="x", padx=pad, pady=int(12 * s), side="bottom")

    events = queue.Queue()
    result = {"ok": False}

    def work():
        try:
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
