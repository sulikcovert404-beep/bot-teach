[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DumpPath,
    [Parameter(Mandatory = $true)]
    [string]$RestoreDatabaseUrl,
    [string]$ReadinessUrl = "http://localhost:8000/health/ready",
    [switch]$SkipMigration
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $DumpPath -PathType Leaf)) {
    throw "Backup dump was not found: $DumpPath"
}
if ([string]::IsNullOrWhiteSpace($RestoreDatabaseUrl)) {
    throw "RestoreDatabaseUrl must be provided and must target a separate database."
}
if ($RestoreDatabaseUrl -match "education(?:[?].*)?$") {
    throw "RestoreDatabaseUrl appears to target the primary database; use a dedicated restore database."
}

Write-Host "Validating backup archive..."
pg_restore --list $DumpPath | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Backup archive validation failed with exit code $LASTEXITCODE"
}

Write-Host "Restoring backup into the dedicated restore database..."
pg_restore --clean --if-exists --exit-on-error --dbname=$RestoreDatabaseUrl $DumpPath
if ($LASTEXITCODE -ne 0) {
    throw "pg_restore failed with exit code $LASTEXITCODE"
}

if (-not $SkipMigration) {
    $previousDatabaseUrl = $env:DATABASE_URL
    try {
        $env:DATABASE_URL = $RestoreDatabaseUrl
        python -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) {
            throw "Migration upgrade failed with exit code $LASTEXITCODE"
        }
    } finally {
        $env:DATABASE_URL = $previousDatabaseUrl
    }
}

Write-Host "Checking readiness endpoint..."
$response = Invoke-RestMethod -Uri $ReadinessUrl -Method Get
if ($response.status -ne "ready") {
    throw "Readiness check failed with status '$($response.status)'."
}

Write-Host "Restore drill passed. Migration head: $($response.migration_head)"
