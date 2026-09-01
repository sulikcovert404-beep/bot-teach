[CmdletBinding()]
param(
    [string]$OutputDirectory = ".\backups"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($env:DATABASE_URL)) {
    throw "DATABASE_URL must be provided through the environment."
}

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$dumpPath = Join-Path $OutputDirectory "education-$timestamp.dump"
$checksumPath = "$dumpPath.sha256"

Write-Host "Creating PostgreSQL custom-format backup..."
pg_dump --format=custom --file=$dumpPath $env:DATABASE_URL
if ($LASTEXITCODE -ne 0) {
    throw "pg_dump failed with exit code $LASTEXITCODE"
}

Write-Host "Validating backup archive..."
pg_restore --list $dumpPath | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "pg_restore archive validation failed with exit code $LASTEXITCODE"
}

$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $dumpPath).Hash
"$hash  $([System.IO.Path]::GetFileName($dumpPath))" | Set-Content -LiteralPath $checksumPath -Encoding ascii
Write-Host "Backup verified: $dumpPath"
Write-Host "SHA-256: $hash"
