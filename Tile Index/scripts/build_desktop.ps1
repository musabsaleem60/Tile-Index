param(
    [string]$ApiBaseUrl,
    [string]$Version = "1.0.0",
    [int]$ApiTimeoutSeconds = 90
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not $ApiBaseUrl) {
    throw "ApiBaseUrl is required. Example: .\scripts\build_desktop.ps1 -ApiBaseUrl https://tile-index-api.onrender.com"
}

$configPyPath = Join-Path $projectRoot "desktop_client\config.py"
$configPy = Get-Content -Path $configPyPath -Raw
$versionPattern = 'APP_VERSION\s*=\s*"[^"]+"'
if ($configPy -notmatch $versionPattern) {
    throw "Could not find APP_VERSION in desktop_client\config.py"
}
$updatedConfigPy = $configPy -replace 'APP_VERSION\s*=\s*"[^"]+"', "APP_VERSION = `"$Version`""
[System.IO.File]::WriteAllText($configPyPath, $updatedConfigPy, [System.Text.UTF8Encoding]::new($false))

$tkProbe = @'
import json
import os
import pathlib
import sys

base = pathlib.Path(sys.base_prefix)
tcl_root = base / "tcl"

def find_library(prefix, marker):
    candidates = sorted(tcl_root.glob(f"{prefix}*"), reverse=True)
    for candidate in candidates:
        if (candidate / marker).exists():
            return str(candidate)
    raise RuntimeError(f"Could not find {marker} under {tcl_root}")

print(json.dumps({
    "tcl_library": find_library("tcl", "init.tcl"),
    "tk_library": find_library("tk", "tk.tcl"),
}))
'@

$tkProbePath = Join-Path ([System.IO.Path]::GetTempPath()) "tileindex_tk_probe.py"
[System.IO.File]::WriteAllText($tkProbePath, $tkProbe, [System.Text.UTF8Encoding]::new($false))
try {
    $tkConfigJson = python $tkProbePath
    if ($LASTEXITCODE -ne 0) {
        throw "Could not resolve Tcl/Tk library paths from the running Python installation."
    }
}
finally {
    Remove-Item -LiteralPath $tkProbePath -ErrorAction SilentlyContinue
}
$tkConfig = $tkConfigJson | ConvertFrom-Json
$env:TCL_LIBRARY = $tkConfig.tcl_library
$env:TK_LIBRARY = $tkConfig.tk_library

python -c "import tkinter as tk; root = tk.Tk(); root.destroy(); print('Tkinter OK')"
if ($LASTEXITCODE -ne 0) {
    throw "Tkinter is not working with TCL_LIBRARY=$env:TCL_LIBRARY and TK_LIBRARY=$env:TK_LIBRARY. Repair/reinstall Python with Tcl/Tk support before building the desktop EXE."
}

python -m pip install pyinstaller

$config = @{
    api_base_url = $ApiBaseUrl
    check_updates = $true
    api_timeout_seconds = $ApiTimeoutSeconds
} | ConvertTo-Json -Depth 3

$configPath = Join-Path $projectRoot "tile_index_config.json"
$config | Set-Content -Path $configPath -Encoding UTF8

python -m PyInstaller --clean -y --noconsole --onedir --name "TileIndex" --add-data "tile_index_config.json;." main.py

$packageDir = Join-Path $projectRoot "dist\TileIndex"
Copy-Item $configPath (Join-Path $packageDir "tile_index_config.json") -Force

Write-Host "Desktop package created at: $packageDir"
Write-Host "Configured API URL: $ApiBaseUrl"
Write-Host "Configured API timeout: $ApiTimeoutSeconds seconds"
Write-Host "Desktop version: $Version"
