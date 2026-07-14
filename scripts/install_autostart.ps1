$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$ExeDir = Join-Path $Root "dist"
$ExePath = Join-Path $ExeDir "AnxietyRadarOverlay.exe"

if (-not (Test-Path $ExePath)) {
    throw "Exe not found. Run scripts\build_overlay.ps1 first."
}

if (-not (Test-Path (Join-Path $ExeDir ".env"))) {
    Write-Warning ".env not found in dist\. Copy your .env there before autostart."
}

$Startup = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $Startup "AnxietyRadarOverlay.lnk"

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $ExePath
$Shortcut.WorkingDirectory = $ExeDir
$Shortcut.WindowStyle = 7
$Shortcut.Description = "AnxietyRadar overlay indicator"
$Shortcut.Save()

Write-Host "Autostart shortcut created:"
Write-Host $ShortcutPath
