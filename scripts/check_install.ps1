# Reports what Chit has on this PC. Usage: powershell -File scripts\check_install.ps1
$app = "$env:LOCALAPPDATA\Programs\Chit\Chit.exe"
$lnk = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Chit.lnk"
$uninst = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{6D2B7C1E-3F4A-4E8B-9C5D-2A7E1B9F4C30}_is1"
$run = (Get-ItemProperty HKCU:\Software\Microsoft\Windows\CurrentVersion\Run -ErrorAction SilentlyContinue).Chit
$data = "$env:LOCALAPPDATA\Chit"
$procs = @(Get-Process Chit -ErrorAction SilentlyContinue).Count

[pscustomobject]@{
    "App installed"         = Test-Path $app
    "Start Menu shortcut"   = Test-Path $lnk
    "Settings > Apps entry" = if (Test-Path $uninst) { (Get-ItemProperty $uninst).DisplayName } else { $false }
    "Start at login"        = if ($run) { $run } else { $false }
    "App data folder"       = if (Test-Path $data) { "{0:N0} MB" -f ((Get-ChildItem $data -Recurse -File | Measure-Object Length -Sum).Sum / 1MB) } else { $false }
    "Running processes"     = $procs
} | Format-List
