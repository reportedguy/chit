# PyInstaller spec for Chit.exe (one-folder, windowed). Build with packaging\build.ps1.
import glob
import os

from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
SRC = os.path.join(ROOT, "src")
SITE = os.path.dirname(os.path.dirname(__import__("pystray").__file__))

datas = [
    (os.path.join(SRC, "chit", "assets"), os.path.join("chit", "assets")),
    (os.path.join(ROOT, "LICENSE"), "licenses"),
    (os.path.join(ROOT, "THIRD_PARTY_NOTICES.md"), "licenses"),
]
# LGPL-3.0 libraries: ship their license texts next to the app.
for pkg in ("pynput", "pystray"):
    for path in glob.glob(os.path.join(SITE, f"{pkg}-*.dist-info", "**", "COPYING*"), recursive=True):
        datas.append((path, os.path.join("licenses", pkg)))

binaries = []
hiddenimports = ["pynput.keyboard._win32", "pynput.mouse._win32", "pystray._win32"]
# Packages with native plugins/data that static analysis can't see.
for pkg in ("openvino", "openvino_genai", "openvino_tokenizers", "onnxruntime", "sounddevice", "_sounddevice_data",
            "pystray", "pynput"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# Chit only loads OpenVINO IR models: drop the importers for other model formats, OpenVINO's
# model-conversion tools (and their opt-in telemetry), link libraries, and onnxruntime's
# Python-side tooling (only its inference runtime is used).
_DROP = ("tensorflow_frontend", "tensorflow_lite_frontend", "pytorch_frontend", "paddle_frontend", "jax_frontend",
         "gguf_frontend", "openvino.lib", os.path.join("openvino", "tools"), os.path.join("openvino", "include"),
         "openvino_telemetry",
         os.path.join("onnxruntime", "transformers"), os.path.join("onnxruntime", "quantization"),
         os.path.join("onnxruntime", "tools"))
_DROP_MODULES = ("onnxruntime.transformers", "onnxruntime.quantization", "onnxruntime.tools", "openvino.tools",
                 "openvino.frontend.tensorflow", "openvino.frontend.pytorch", "openvino.frontend.jax", "openvino.torch",
                 "openvino_telemetry")


def _keep(entry):
    return not any(d in entry[0] or d in entry[1] for d in _DROP)


datas = [e for e in datas if _keep(e)]
binaries = [e for e in binaries if _keep(e)]
hiddenimports = [h for h in hiddenimports if not h.startswith(_DROP_MODULES)]

a = Analysis(
    [os.path.join(SPECPATH, "launcher.py")],
    pathex=[SRC],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["pytest", "ruff", "matplotlib", "IPython", "jupyter", "torch", "tensorflow", "pandas", "scipy",
              "openvino_telemetry", "openvino.tools"],
    # LGPL-3.0: keep pynput and pystray as plain .py files so users can replace them.
    module_collection_mode={"pynput": "py", "pystray": "py"},
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Chit",
    icon=os.path.join(SPECPATH, "chit.ico"),
    version=os.path.join(ROOT, "build", "version_info.txt"),
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Chit", upx=False)
