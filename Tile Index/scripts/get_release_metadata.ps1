param(
    [Parameter(Mandatory = $true)]
    [string]$FilePath
)

$ErrorActionPreference = "Stop"

$resolved = Resolve-Path $FilePath
$hash = Get-FileHash -Path $resolved -Algorithm SHA256
$item = Get-Item -Path $resolved
$signature = Get-AuthenticodeSignature -LiteralPath $item.FullName

[PSCustomObject]@{
    file = $item.FullName
    sha256 = $hash.Hash.ToLowerInvariant()
    file_size_bytes = $item.Length
    signature_status = $signature.Status.ToString()
    signature_publisher = if ($signature.SignerCertificate) { $signature.SignerCertificate.Subject } else { "" }
    signature_thumbprint = if ($signature.SignerCertificate) { $signature.SignerCertificate.Thumbprint } else { "" }
} | ConvertTo-Json
