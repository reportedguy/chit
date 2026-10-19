# Builds build\dist\Chit\Chit.exe (PyInstaller) and the installer (Inno Setup), then collects
# release files in build\release. The version comes from src\chit\__init__.py.
# Usage (from the repo root, with the dev environment installed):
#   powershell -ExecutionPolicy Bypass -File packaging\build.ps1
param([string]$Python = "")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not $Python) {
    $venv = Join-Path $root ".venv\Scripts\python.exe"
    $Python = if (Test-Path $venv) { $venv } else { "python" }
}

& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Tests failed" }

$version = (& $Python -c "import chit; print(chit.__version__)").Trim()
$major, $minor, $patch = $version.Split(".")
New-Item -ItemType Directory -Force build | Out-Null
(Get-Content packaging\version_info.txt -Raw).Replace("{VERSION}", $version).Replace("{MAJOR}", $major).
    Replace("{MINOR}", $minor).Replace("{PATCH}", $patch) | Set-Content build\version_info.txt -Encoding utf8

& $Python -c @"
from PIL import Image
from chit.icon import app_icon, save_icon
save_icon(r'packaging\chit.ico', 'dark')
small = Image.new('RGB', (110, 110), 'white')  # installer wizard corner image
small.paste(app_icon(110, 'light'), (0, 0), app_icon(110, 'light'))
small.save(r'packaging\wizard_small.bmp')
"@

& $Python -m PyInstaller packaging\chit.spec --noconfirm --clean --distpath build\dist --workpath build\work
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
          "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup 6 not found. Install it with: winget install JRSoftware.InnoSetup" }
& $iscc "/DAppVersion=$version" packaging\installer.iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }

# Release folder: versioned installer, checksum, and logos for a download page.
$rel = Join-Path $root "build\release"
New-Item -ItemType Directory -Force $rel | Out-Null
$setup = Join-Path $rel "ChitSetup-$version.exe"
Copy-Item build\ChitSetup.exe $setup -Force
$hash = (Get-FileHash $setup -Algorithm SHA256).Hash.ToLower()
"$hash  ChitSetup-$version.exe" | Set-Content (Join-Path $rel "ChitSetup-$version.exe.sha256") -Encoding ascii
& $Python -c "from chit.icon import app_icon; [app_icon(512, t).save(rf'$rel\chit-logo-{t}.png') for t in ('light', 'dark')]"
Get-ChildItem $rel | Select-Object Name, @{n = "SizeMB"; e = { [math]::Round($_.Length / 1MB, 1) } }
