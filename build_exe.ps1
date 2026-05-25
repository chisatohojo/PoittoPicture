$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    python -m venv .venv
}

& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "PoittoPicture" `
    --icon "assets\app_icon.ico" `
    --add-data "assets\app_icon.ico;assets" `
    "poitto_picture.py"
