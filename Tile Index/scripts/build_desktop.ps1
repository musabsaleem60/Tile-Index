param(
    [string]$ApiBaseUrl,
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

if (-not $ApiBaseUrl) {
    throw "ApiBaseUrl is required. Example: .\scripts\build_desktop.ps1 -ApiBaseUrl https://tile-index-api.onrender.com"
}

python -m pip install pyinstaller

$config = @{
    api_base_url = $ApiBaseUrl
    check_updates = $true
} | ConvertTo-Json -Depth 3

$configPath = Join-Path $projectRoot "tile_index_config.json"
$config | Set-Content -Path $configPath -Encoding UTF8

python -m PyInstaller --noconsole --onedir --name "TileIndex" --add-data "tile_index_config.json;." main.py

$packageDir = Join-Path $projectRoot "dist\TileIndex"
Copy-Item $configPath (Join-Path $packageDir "tile_index_config.json") -Force

Write-Host "Desktop package created at: $packageDir"
Write-Host "Configured API URL: $ApiBaseUrl"
