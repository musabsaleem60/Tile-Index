param(
    [string]$PackageDir = ".\dist\TileIndex",
    [string]$CertName = "Tile Index Internal Code Signing",
    [switch]$TrustForCurrentUser = $true
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$exePath = Join-Path $PackageDir "TileIndex.exe"
if (-not (Test-Path $exePath)) {
    throw "TileIndex.exe was not found at: $exePath"
}

$subject = "CN=$CertName"
$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
    Where-Object { $_.Subject -eq $subject } |
    Sort-Object NotAfter -Descending |
    Select-Object -First 1

if (-not $cert) {
    $cert = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject $subject `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -KeyAlgorithm RSA `
        -KeyLength 3072 `
        -HashAlgorithm SHA256 `
        -NotAfter (Get-Date).AddYears(3)
}

$certExportPath = Join-Path $PackageDir "TileIndex-CodeSigning.cer"
Export-Certificate -Cert $cert -FilePath $certExportPath | Out-Null

if ($TrustForCurrentUser) {
    Import-Certificate -FilePath $certExportPath -CertStoreLocation "Cert:\CurrentUser\Root" | Out-Null
    Import-Certificate -FilePath $certExportPath -CertStoreLocation "Cert:\CurrentUser\TrustedPublisher" | Out-Null
}

$signature = Set-AuthenticodeSignature -FilePath $exePath -Certificate $cert -HashAlgorithm SHA256

Write-Host "Signed EXE: $exePath"
Write-Host "Signature status: $($signature.Status)"
Write-Host "Certificate exported to: $certExportPath"
Write-Host ""
Write-Host "Install this certificate on each client laptop:"
Write-Host "  $certExportPath"
