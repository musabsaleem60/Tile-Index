param(
    [string]$Version,
    [string]$PackageDir = ".\dist\TileIndex",
    [string]$OutputDir = ".\dist\installer",
    [string]$CertThumbprint = "5654E094C05235013364F2B2B3ACB04DAB803913"
)

$ErrorActionPreference = "Stop"

if (-not $Version) {
    throw "Version is required. Example: .\scripts\build_installer.ps1 -Version 1.2.0"
}

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue
if (-not $iscc) {
    $candidate = Get-ChildItem -Path "${env:ProgramFiles(x86)}\Inno Setup 6", "${env:ProgramFiles}\Inno Setup 6", "${env:LOCALAPPDATA}\Programs\Inno Setup 6" -Filter ISCC.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($candidate) {
        $iscc = $candidate
    }
}
if (-not $iscc) {
    throw "Inno Setup 6 ISCC.exe was not found. Install Inno Setup before building the installer."
}
$isccPath = if ($iscc.Source) { $iscc.Source } else { $iscc.FullName }

$resolvedPackage = Resolve-Path $PackageDir
if (-not (Test-Path (Join-Path $resolvedPackage "TileIndex.exe"))) {
    throw "TileIndex.exe was not found in $resolvedPackage"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$resolvedOutput = Resolve-Path $OutputDir
$issPath = Join-Path $projectRoot "scripts\TileIndexInstaller.iss"

& $isccPath `
    /DAppVersion="$Version" `
    /DPackageDir="$resolvedPackage" `
    /DOutputDir="$resolvedOutput" `
    /DCertThumbprint="$CertThumbprint" `
    $issPath

if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup failed with exit code $LASTEXITCODE"
}

$installer = Join-Path $resolvedOutput "TileIndexSetup-$Version.exe"
if (-not (Test-Path $installer)) {
    throw "Expected installer was not created: $installer"
}

Write-Host "Installer created at: $installer"
