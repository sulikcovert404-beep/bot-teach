[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DumpPath,
    [Parameter(Mandatory = $true)]
    [string]$RestoreDatabaseUrl,
    [Parameter(Mandatory = $true)]
    [ValidateSet('20261003_0029', '20261004_0032', '20261003_0030', '20261003_0031', '20261004_0033')]
    [string]$MigrationTarget,
    [string]$ReadinessUrl = "http://localhost:8000/health/ready",
    [switch]$SkipMigration
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $DumpPath -PathType Leaf)) {
    throw "Backup dump was not found: $DumpPath"
}
try {
    $databaseUri = [Uri]$RestoreDatabaseUrl
} catch {
    throw "RestoreDatabaseUrl must be a valid PostgreSQL URI for a local disposable database."
}
$safeHosts = @('localhost', '127.0.0.1', '::1')
$restoreHost = $databaseUri.DnsSafeHost.Trim('[', ']').ToLowerInvariant()
$restoreDatabase = [Uri]::UnescapeDataString($databaseUri.AbsolutePath)
if ($databaseUri.Scheme -notin @('postgresql', 'postgresql+asyncpg') -or
    $restoreHost -notin $safeHosts -or
    $restoreDatabase -notmatch '^/gate738aa_restore_[a-z0-9_]+$' -or
    $databaseUri.Query -or $databaseUri.Fragment) {
    throw "Restore target refused; only a loopback gate738aa_restore_* database is allowed."
}
try {
    $readinessUri = [Uri]$ReadinessUrl
} catch {
    throw "ReadinessUrl must be a local HTTP(S) URL."
}
$readinessHost = $readinessUri.DnsSafeHost.Trim('[', ']').ToLowerInvariant()
if ($readinessUri.Scheme -notin @('http', 'https') -or $readinessHost -notin $safeHosts -or
    $readinessUri.UserInfo -or $readinessUri.Query -or $readinessUri.Fragment) {
    throw "Readiness target refused; only a loopback HTTP(S) endpoint is allowed."
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
    $previousExpectedHead = $env:EXPECTED_MIGRATION_HEAD
    try {
        $env:DATABASE_URL = $RestoreDatabaseUrl
        $env:EXPECTED_MIGRATION_HEAD = $MigrationTarget
        & python -B scripts/gate738p_contract_upgrade.py
        if ($LASTEXITCODE -ne 0) {
            throw "Canonical migration runner failed with exit code $LASTEXITCODE"
        }
    } finally {
        $env:DATABASE_URL = $previousDatabaseUrl
        $env:EXPECTED_MIGRATION_HEAD = $previousExpectedHead
    }
}

Write-Host "Checking readiness endpoint..."
$response = Invoke-RestMethod -Uri $ReadinessUrl -Method Get
if ($response.status -ne "ready" -or $response.migration_head -ne $MigrationTarget) {
    throw "Readiness check failed with status '$($response.status)'."
}

Write-Host "Restore drill passed at the requested migration target."
