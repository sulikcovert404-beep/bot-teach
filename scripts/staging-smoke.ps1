[CmdletBinding()]
param(
    [string]$BaseUrl = "http://localhost:8000",
    [int]$Attempts = 30,
    [int]$DelaySeconds = 2,
    [string]$ExpectedMigrationHead = "e2f3a4b5c6d7"
)

$ErrorActionPreference = "Stop"

Write-Host "Starting staging services..."
docker compose up -d db migrate api
if ($LASTEXITCODE -ne 0) {
    throw "Compose startup failed with exit code $LASTEXITCODE"
}

$readyUrl = "$BaseUrl/health/ready"
for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
    try {
        $response = Invoke-RestMethod -Uri $readyUrl -Method Get
        if ($response.status -eq "ready" -and $response.migration_head -eq $ExpectedMigrationHead) {
            Write-Host "Readiness passed at migration head $($response.migration_head)."
            exit 0
        }
        if ($response.status -eq "ready") {
            throw "Unexpected migration head: $($response.migration_head); expected $ExpectedMigrationHead"
        }
    } catch {
        if ($attempt -eq $Attempts) {
            throw "Readiness check failed after $Attempts attempts: $($_.Exception.Message)"
        }
    }
    Start-Sleep -Seconds $DelaySeconds
}

throw "Readiness check did not pass."
