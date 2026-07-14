$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = Join-Path $Root "venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "venv not found. Run: python -m venv venv"
}

& $Python -m pip install -r requirements-build.txt

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --noconsole `
    --name AnxietyRadarOverlay `
    --paths $Root `
    (Join-Path $Root "overlay.py")

$DistDir = Join-Path $Root "dist"
$EnvExample = Join-Path $Root ".env.example"
$DistEnvExample = Join-Path $DistDir ".env.example"

Copy-Item $EnvExample $DistEnvExample -Force

Write-Host ""
Write-Host "Done: $DistDir\AnxietyRadarOverlay.exe"
Write-Host "Copy .env next to the exe (see .env.example) before running."
